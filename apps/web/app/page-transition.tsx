"use client";

import { usePathname } from "next/navigation";

/** Re-keys on route change so page content fades/slides in on every
 * navigation. Respects prefers-reduced-motion (handled globally in CSS). */
export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className="animate-fade-up">
      {children}
    </div>
  );
}
