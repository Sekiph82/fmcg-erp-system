import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=visits&drawer=create");
}
