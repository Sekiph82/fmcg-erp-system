import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=trade-spend&drawer=create");
}
