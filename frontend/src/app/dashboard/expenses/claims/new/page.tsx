import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/hr?tab=expenses&drawer=create");
}
