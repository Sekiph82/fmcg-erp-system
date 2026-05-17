import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/inventory?tab=shelf-life");
}
