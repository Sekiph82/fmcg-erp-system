import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/procurement?tab=landed-cost");
}
