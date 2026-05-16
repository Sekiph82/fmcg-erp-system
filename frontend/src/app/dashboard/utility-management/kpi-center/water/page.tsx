import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/utility-management?tab=kpi-center");
}
