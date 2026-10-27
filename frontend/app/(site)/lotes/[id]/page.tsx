import { LotRoom } from "./lot-room";

export default async function LotPage({ params }: PageProps<"/lotes/[id]">) {
  const { id } = await params;
  return <LotRoom id={id} />;
}
