import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/hr?tab=appraisals&drawer=create");
}
