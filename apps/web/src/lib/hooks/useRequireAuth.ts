import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { hasValidToken } from "@/lib/api";

export const useRequireAuth = () => {
  const router = useRouter();
  useEffect(() => {
    if (!hasValidToken()) {
      router.push("/login");
    }
  }, [router]);
};
