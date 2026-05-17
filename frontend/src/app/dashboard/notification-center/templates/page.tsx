import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/communication?tab=notifications");
}
