import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/finance?tab=bank-recon");
}
