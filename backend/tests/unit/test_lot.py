from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from account.domain.user import UserId
from auction.domain.entities.lot import DisplayStatus, Lot, LotId, LotStatus
from shared.domain.exceptions import DomainError

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
MIN = timedelta(minutes=1)


def make_lot(
    starts_in=-10 * MIN, ends_in=60 * MIN, starting=D("100.00"), increment=D("5.00")
) -> Lot:
    return Lot.create(
        id=LotId(),
        auctioneer_id=UserId(),
        external_id="1",
        title="Obra",
        image_url=None,
        attributes={},
        starting_bid=starting,
        min_increment=increment,
        starts_at=NOW + starts_in,
        ends_at=NOW + ends_in,
        chain_head="h0",
        now=NOW,
    )


def refusal(fn, *args) -> DomainError:
    with pytest.raises(DomainError) as exc:
        fn(*args)
    return exc.value


@pytest.mark.parametrize(
    "starting,increment",
    [(D("0"), D("1.00")), (D("1.00"), D("0")), (D("-1.00"), D("1.00")), (D("1.001"), D("1.00"))],
)
def test_create_requires_positive_amounts(starting, increment):
    assert refusal(make_lot, -MIN, MIN, starting, increment).code == "INVALID_AMOUNT"


def test_create_requires_end_after_start_and_in_the_future():
    assert refusal(make_lot, 10 * MIN, 5 * MIN).code == "INVALID_SCHEDULE"
    assert refusal(make_lot, -10 * MIN, -MIN).code == "INVALID_SCHEDULE"
    assert make_lot(starts_in=-10 * MIN, ends_in=MIN).status == LotStatus.ACTIVE


def test_display_status_follows_the_clock():
    lot = make_lot(starts_in=10 * MIN, ends_in=20 * MIN)

    assert lot.display_status(NOW) == DisplayStatus.SCHEDULED
    assert lot.display_status(NOW + 10 * MIN) == DisplayStatus.LIVE
    assert lot.display_status(NOW + 20 * MIN) == DisplayStatus.ENDED


def test_display_status_of_cancelled_and_settled():
    cancelled, settled = make_lot(), make_lot(ends_in=MIN)
    cancelled.cancel(NOW)
    settled.mark_settled(NOW + MIN)

    assert cancelled.display_status(NOW) == DisplayStatus.CANCELLED
    assert settled.display_status(NOW) == DisplayStatus.ENDED


def test_first_bid_at_least_starting_bid():
    lot = make_lot(starting=D("100.00"))

    error = refusal(lot.check_bid, UserId(), D("99.99"), NOW)
    assert (error.code, error.details) == ("BELOW_MINIMUM", {"min_amount": D("100.00")})
    assert error.message == "O lance mínimo é R$ 100,00."
    lot.apply_bid(UserId(), D("100.00"), NOW, "h1")  # equal is accepted


def test_first_bid_above_starting_bid_is_accepted():
    lot = make_lot(starting=D("100.00"))

    lot.apply_bid(UserId(), D("250.00"), NOW, "h1")

    assert lot.current_bid == D("250.00")


def test_next_bids_need_current_plus_increment():
    lot = make_lot(starting=D("100.00"), increment=D("5.00"))
    lot.apply_bid(UserId(), D("100.00"), NOW, "h1")

    assert lot.min_next_bid() == D("105.00")
    assert refusal(lot.check_bid, UserId(), D("104.99"), NOW).code == "BELOW_MINIMUM"
    lot.apply_bid(UserId(), D("105.00"), NOW, "h2")
    assert (lot.bid_count, lot.chain_head) == (2, "h2")


def test_leader_cannot_outbid_themselves():
    lot, ana = make_lot(), UserId()
    lot.apply_bid(ana, D("100.00"), NOW, "h1")

    assert refusal(lot.check_bid, ana, D("200.00"), NOW).code == "ALREADY_WINNING"


def test_bids_only_while_live():
    scheduled = make_lot(starts_in=MIN)
    ended = make_lot(ends_in=MIN)
    cancelled = make_lot()
    cancelled.cancel(NOW)

    assert refusal(scheduled.check_bid, UserId(), D("100.00"), NOW).code == "LOT_NOT_STARTED"
    assert refusal(ended.check_bid, UserId(), D("100.00"), NOW + MIN).code == "LOT_ENDED"
    assert refusal(cancelled.check_bid, UserId(), D("100.00"), NOW).code == "LOT_ENDED"


def test_apply_bid_reports_previous_leader():
    lot, ana, bia = make_lot(), UserId(), UserId()

    first = lot.apply_bid(ana, D("100.00"), NOW, "h1")
    second = lot.apply_bid(bia, D("110.00"), NOW, "h2")

    assert (first.previous_leader_id, first.previous_amount) == (None, None)
    assert (second.previous_leader_id, second.previous_amount) == (ana, D("100.00"))
    assert lot.leader_id == bia


def test_bid_in_last_two_minutes_extends_to_now_plus_two():
    lot = make_lot(ends_in=90 * timedelta(seconds=1))

    outcome = lot.apply_bid(UserId(), D("100.00"), NOW, "h1")

    assert outcome.extended
    assert lot.ends_at == NOW + 2 * MIN


def test_bid_exactly_two_minutes_before_end_extends():
    lot = make_lot(ends_in=2 * MIN)

    assert lot.apply_bid(UserId(), D("100.00"), NOW, "h1").extended


def test_bid_before_last_two_minutes_does_not_extend():
    lot = make_lot(ends_in=2 * MIN + timedelta(seconds=1))
    end = lot.ends_at

    assert not lot.apply_bid(UserId(), D("100.00"), NOW, "h1").extended
    assert lot.ends_at == end


def test_cancel_rules():
    with_bids = make_lot()
    with_bids.apply_bid(UserId(), D("100.00"), NOW, "h1")
    ended = make_lot(ends_in=MIN)

    assert refusal(with_bids.cancel, NOW).code == "LOT_HAS_BIDS"
    assert refusal(ended.cancel, NOW + MIN).code == "LOT_NOT_CANCELLABLE"
    with_bids.cancel(NOW, allow_with_bids=True)
    assert with_bids.status == LotStatus.CANCELLED
    assert refusal(with_bids.cancel, NOW).code == "LOT_NOT_CANCELLABLE"


def test_settle_only_after_end():
    lot = make_lot(ends_in=MIN)

    assert not lot.is_due_for_settlement(NOW)
    assert refusal(lot.mark_settled, NOW).code == "LOT_NOT_SETTLEABLE"
    lot.mark_settled(NOW + MIN)
    assert (lot.status, lot.settled_at) == (LotStatus.SETTLED, NOW + MIN)
    assert not lot.is_due_for_settlement(NOW + MIN)


def test_bid_with_more_than_two_decimals_is_refused():
    lot = make_lot()

    assert refusal(lot.check_bid, UserId(), D("100.001"), NOW).code == "INVALID_AMOUNT"


def test_amounts_are_normalised_to_two_places():
    lot = make_lot(starting=D("100"), increment=D("0.5"))
    lot.apply_bid(UserId(), D("100"), NOW, "h1")

    assert str(lot.starting_bid) == "100.00"
    assert str(lot.current_bid) == "100.00"
    assert str(lot.min_next_bid()) == "100.50"
