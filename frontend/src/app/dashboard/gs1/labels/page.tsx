import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/compliance?tab=gs1");
}
