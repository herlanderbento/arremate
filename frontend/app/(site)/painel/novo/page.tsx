"use client";

import { RequireAuth } from "@/components";
import { NewLotForm } from "./new-lot-form";

export default function NewLotPage() {
  return <RequireAuth role="AUCTIONEER">{() => <NewLotForm />}</RequireAuth>;
}
