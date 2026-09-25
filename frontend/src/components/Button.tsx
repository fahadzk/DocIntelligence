import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode; icon?: IconName; variant?: "primary" | "secondary" | "danger" | "quiet" | "ghost" };
export function Button({ children, icon, variant = "secondary", className = "", ...props }: Props) {
  return <button className={`button button-${variant} ${className}`} {...props}>{icon && <Icon name={icon} size={16} />}{children}</button>;
}
