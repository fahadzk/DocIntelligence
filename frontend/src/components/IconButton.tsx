import type { ButtonHTMLAttributes } from "react";
export function IconButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) { return <button className={`icon-button ${className}`} {...props} />; }
