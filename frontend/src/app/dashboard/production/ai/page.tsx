import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/production?tab=plans");
}
