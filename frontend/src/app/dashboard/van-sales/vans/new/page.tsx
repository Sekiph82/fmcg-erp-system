import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/sales?tab=van-sales&drawer=create");
}
