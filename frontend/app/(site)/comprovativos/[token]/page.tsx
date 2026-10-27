import { ReceiptView } from "./receipt-view";

export default async function ReceiptPage({ params }: PageProps<"/comprovativos/[token]">) {
  const { token } = await params;
  return <ReceiptView token={token} />;
}
