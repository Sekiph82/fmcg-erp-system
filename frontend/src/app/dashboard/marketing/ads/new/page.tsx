import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=ads&drawer=create");
}
