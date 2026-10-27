import { AuditView } from "./audit-view";

export default async function AuditPage({ params }: PageProps<"/auditoria/[id]">) {
  const { id } = await params;
  return <AuditView lotId={id} />;
}
