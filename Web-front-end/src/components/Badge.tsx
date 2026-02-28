import type { ReactNode } from "react";
import { clsx } from "clsx";

interface BadgeProps {
  children: ReactNode;
  variant?: "green" | "red" | "blue" | "gray";
}

const variants = {
  green: "bg-green-100 text-green-800",
  red: "bg-red-100 text-red-800",
  blue: "bg-blue-100 text-blue-800",
  gray: "bg-gray-100 text-gray-700",
};

export function Badge({ children, variant = "gray" }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        variants[variant]
      )}
    >
      {children}
    </span>
  );
}
