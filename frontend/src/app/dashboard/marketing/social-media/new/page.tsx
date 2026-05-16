import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=social-media&drawer=create");
}
