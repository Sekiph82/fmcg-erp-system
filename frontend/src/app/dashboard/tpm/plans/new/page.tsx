import { redirect } from "next/navigation";

export default function Page() {
  redirect("/dashboard/marketing?tab=tpm&drawer=create");
}
