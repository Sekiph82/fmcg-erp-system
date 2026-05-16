import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=segments&drawer=create");
}
