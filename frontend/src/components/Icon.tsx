import type { ReactElement, SVGProps } from "react";

export type IconName =
  | "server"
  | "schedule"
  | "bot"
  | "integration"
  | "config"
  | "storage"
  | "close"
  | "arrowLeft"
  | "arrowRight"
  | "lock"
  | "send"
  | "agent"
  | "sun"
  | "moon"
  | "loader"
  | "zoomIn"
  | "zoomOut"
  | "fit"
  | "brand";

const SHAPES: Record<IconName, ReactElement> = {
  server: (
    <>
      <path
        opacity="0.4"
        d="M19.32 10H4.69002C3.21002 10 2.01001 8.79 2.01001 7.32V4.68999C2.01001 3.20999 3.22002 2.00999 4.69002 2.00999H19.32C20.8 2.00999 22 3.21999 22 4.68999V7.32C22 8.79 20.79 10 19.32 10Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M19.32 22H4.69002C3.21002 22 2.01001 20.79 2.01001 19.32V16.69C2.01001 15.21 3.22002 14.01 4.69002 14.01H19.32C20.8 14.01 22 15.22 22 16.69V19.32C22 20.79 20.79 22 19.32 22Z"
        fill="currentColor"
      />
      <path
        d="M6 7.75C5.59 7.75 5.25 7.41 5.25 7V5C5.25 4.59 5.59 4.25 6 4.25C6.41 4.25 6.75 4.59 6.75 5V7C6.75 7.41 6.41 7.75 6 7.75Z"
        fill="currentColor"
      />
      <path
        d="M10 7.75C9.59 7.75 9.25 7.41 9.25 7V5C9.25 4.59 9.59 4.25 10 4.25C10.41 4.25 10.75 4.59 10.75 5V7C10.75 7.41 10.41 7.75 10 7.75Z"
        fill="currentColor"
      />
      <path
        d="M6 19.75C5.59 19.75 5.25 19.41 5.25 19V17C5.25 16.59 5.59 16.25 6 16.25C6.41 16.25 6.75 16.59 6.75 17V19C6.75 19.41 6.41 19.75 6 19.75Z"
        fill="currentColor"
      />
      <path
        d="M10 19.75C9.59 19.75 9.25 19.41 9.25 19V17C9.25 16.59 9.59 16.25 10 16.25C10.41 16.25 10.75 16.59 10.75 17V19C10.75 19.41 10.41 19.75 10 19.75Z"
        fill="currentColor"
      />
      <path
        d="M18 6.75H14C13.59 6.75 13.25 6.41 13.25 6C13.25 5.59 13.59 5.25 14 5.25H18C18.41 5.25 18.75 5.59 18.75 6C18.75 6.41 18.41 6.75 18 6.75Z"
        fill="currentColor"
      />
      <path
        d="M18 18.75H14C13.59 18.75 13.25 18.41 13.25 18C13.25 17.59 13.59 17.25 14 17.25H18C18.41 17.25 18.75 17.59 18.75 18C18.75 18.41 18.41 18.75 18 18.75Z"
        fill="currentColor"
      />
    </>
  ),
  schedule: (
    <>
      <path
        opacity="0.4"
        d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
        fill="currentColor"
      />
      <path
        d="M15.7101 15.93C15.5801 15.93 15.4501 15.9 15.3301 15.82L12.2301 13.97C11.4601 13.51 10.8901 12.5 10.8901 11.61V7.51001C10.8901 7.10001 11.2301 6.76001 11.6401 6.76001C12.0501 6.76001 12.3901 7.10001 12.3901 7.51001V11.61C12.3901 11.97 12.6901 12.5 13.0001 12.68L16.1001 14.53C16.4601 14.74 16.5701 15.2 16.3601 15.56C16.2101 15.8 15.9601 15.93 15.7101 15.93Z"
        fill="currentColor"
      />
    </>
  ),
  bot: (
    <>
      <path
        opacity="0.4"
        d="M8.5 18.97H8C4 18.97 2 17.97 2 12.97V7.96997C2 3.96997 4 1.96997 8 1.96997H16C20 1.96997 22 3.96997 22 7.96997V12.97C22 16.97 20 18.97 16 18.97H15.5C15.19 18.97 14.89 19.12 14.7 19.37L13.2 21.37C12.54 22.25 11.46 22.25 10.8 21.37L9.29999 19.37C9.13999 19.15 8.78 18.97 8.5 18.97Z"
        fill="currentColor"
      />
      <path
        d="M8 13.45C7.81 13.45 7.62 13.38 7.47 13.23L5.47 11.23C5.18 10.94 5.18 10.46 5.47 10.17L7.47 8.16995C7.76 7.87995 8.24 7.87995 8.53 8.16995C8.82 8.45995 8.82 8.93995 8.53 9.22995L7.06 10.7L8.53 12.17C8.82 12.46 8.82 12.94 8.53 13.23C8.38 13.38 8.19 13.45 8 13.45Z"
        fill="currentColor"
      />
      <path
        d="M16 13.45C15.81 13.45 15.62 13.38 15.47 13.23C15.18 12.94 15.18 12.46 15.47 12.17L16.94 10.7L15.47 9.22995C15.18 8.93995 15.18 8.45995 15.47 8.16995C15.76 7.87995 16.24 7.87995 16.53 8.16995L18.53 10.17C18.82 10.46 18.82 10.94 18.53 11.23L16.53 13.23C16.38 13.38 16.19 13.45 16 13.45Z"
        fill="currentColor"
      />
      <path
        d="M11 13.78C10.9 13.78 10.8 13.76 10.7 13.72C10.32 13.56 10.14 13.12 10.31 12.73L12.31 8.05999C12.47 7.67999 12.91 7.49998 13.3 7.66998C13.68 7.82998 13.86 8.26997 13.69 8.65997L11.69 13.33C11.57 13.61 11.29 13.78 11 13.78Z"
        fill="currentColor"
      />
    </>
  ),
  integration: (
    <>
      <path
        d="M19.07 14.24C18.78 14.53 18.32 14.53 18.04 14.24C17.75 13.95 17.75 13.49 18.04 13.21C20.04 11.21 20.04 7.95998 18.04 5.96998C16.04 3.97998 12.79 3.96998 10.8 5.96998C8.81003 7.96998 8.80003 11.22 10.8 13.21C11.09 13.5 11.09 13.96 10.8 14.24C10.51 14.53 10.05 14.53 9.77003 14.24C7.20003 11.67 7.20003 7.48998 9.77003 4.92998C12.34 2.36998 16.52 2.35998 19.08 4.92998C21.64 7.49998 21.64 11.67 19.07 14.24Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M19.07 4.92994C21.64 7.49994 21.64 11.6699 19.07 14.2399C18.19 15.1199 17.11 15.6999 15.98 15.9799C16.51 13.8199 15.93 11.4499 14.24 9.75994C12.55 8.06994 10.18 7.48994 8.02002 8.01994C8.30002 6.88994 8.87002 5.80994 9.76002 4.92994C12.33 2.35994 16.5 2.35994 19.07 4.92994Z"
        fill="currentColor"
      />
      <path
        d="M4.92997 9.75998C5.21997 9.46998 5.67997 9.46998 5.95997 9.75998C6.24997 10.05 6.24997 10.51 5.95997 10.79C3.95997 12.79 3.95997 16.04 5.95997 18.03C7.95997 20.02 11.21 20.03 13.2 18.03C15.19 16.03 15.2 12.78 13.2 10.79C12.91 10.5 12.91 10.04 13.2 9.75998C13.49 9.46998 13.95 9.46998 14.23 9.75998C16.8 12.33 16.8 16.51 14.23 19.07C11.66 21.63 7.47997 21.64 4.91997 19.07C2.35997 16.5 2.35997 12.33 4.92997 9.75998Z"
        fill="currentColor"
      />
      <path
        opacity="0.5"
        d="M14.2399 9.76C15.9299 11.45 16.5099 13.82 15.9799 15.98C15.6999 17.11 15.1199 18.19 14.2399 19.07C11.6699 21.64 7.49994 21.64 4.92994 19.07C2.35994 16.5 2.35994 12.33 4.92994 9.76C5.80994 8.87 6.88994 8.3 8.01994 8.02C10.1799 7.49 12.5499 8.07 14.2399 9.76Z"
        fill="currentColor"
      />
    </>
  ),
  config: (
    <>
      <path
        opacity="0.4"
        d="M21.23 7.61998H15.69C15.31 7.61998 15 7.30998 15 6.91998C15 6.53998 15.31 6.22998 15.69 6.22998H21.23C21.61 6.22998 21.92 6.53998 21.92 6.91998C21.92 7.30998 21.61 7.61998 21.23 7.61998Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M6.46008 7.61999H2.77008C2.39008 7.61999 2.08008 7.30999 2.08008 6.92999C2.08008 6.54999 2.39008 6.23999 2.77008 6.23999H6.46008C6.84008 6.23999 7.15008 6.54999 7.15008 6.92999C7.15008 7.30999 6.84008 7.61999 6.46008 7.61999Z"
        fill="currentColor"
      />
      <path
        d="M10.15 10.84C12.3149 10.84 14.07 9.08496 14.07 6.92C14.07 4.75504 12.3149 3 10.15 3C7.98502 3 6.22998 4.75504 6.22998 6.92C6.22998 9.08496 7.98502 10.84 10.15 10.84Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M21.2301 17.77H17.5401C17.1601 17.77 16.8501 17.46 16.8501 17.08C16.8501 16.7 17.1601 16.39 17.5401 16.39H21.2301C21.6101 16.39 21.9201 16.7 21.9201 17.08C21.9201 17.46 21.6101 17.77 21.2301 17.77Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M8.31008 17.77H2.77008C2.39008 17.77 2.08008 17.46 2.08008 17.08C2.08008 16.7 2.39008 16.39 2.77008 16.39H8.31008C8.69008 16.39 9.00008 16.7 9.00008 17.08C9.00008 17.46 8.69008 17.77 8.31008 17.77Z"
        fill="currentColor"
      />
      <path
        d="M13.8502 21C16.0151 21 17.7702 19.245 17.7702 17.08C17.7702 14.9151 16.0151 13.16 13.8502 13.16C11.6852 13.16 9.93018 14.9151 9.93018 17.08C9.93018 19.245 11.6852 21 13.8502 21Z"
        fill="currentColor"
      />
    </>
  ),
  storage: (
    <>
      <path
        d="M22 11.07V16.65C22 19.6 19.6 22 16.65 22H7.35C4.4 22 2 19.6 2 16.65V9.44H21.74C21.89 9.89 21.97 10.35 21.99 10.84C22 10.91 22 11 22 11.07Z"
        fill="currentColor"
      />
      <path
        opacity="0.4"
        d="M21.74 9.44H2V6.42C2 3.98 3.98 2 6.42 2H8.75C10.38 2 10.89 2.53 11.54 3.4L12.94 5.26C13.25 5.67 13.29 5.73 13.87 5.73H16.66C19.03 5.72 21.05 7.28 21.74 9.44Z"
        fill="currentColor"
      />
    </>
  ),
  close: (
    <g transform="rotate(45 12 12)">
      <path
        d="M6 12H18"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M12 18V6"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </g>
  ),
  arrowLeft: (
    <>
      <path
        d="M15 19.92L8.48 13.4C7.71 12.63 7.71 11.37 8.48 10.6L15 4.07996"
        strokeWidth="1.5"
        strokeMiterlimit="10"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  arrowRight: (
    <>
      <path
        d="M8.91 19.92L15.43 13.4C16.2 12.63 16.2 11.37 15.43 10.6L8.91 4.07996"
        strokeWidth="1.5"
        strokeMiterlimit="10"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  lock: (
    <>
      <path
        d="M6 10V8C6 4.69 7 2 12 2C17 2 18 4.69 18 8V10"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M14.5 16C14.5 17.3807 13.3807 18.5 12 18.5C10.6193 18.5 9.5 17.3807 9.5 16C9.5 14.6193 10.6193 13.5 12 13.5C13.3807 13.5 14.5 14.6193 14.5 16Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M17 22H7C3 22 2 21 2 17V15C2 11 3 10 7 10H17C21 10 22 11 22 15V17C22 21 21 22 17 22Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  send: (
    <>
      <path
        d="M7.40018 6.31991L15.8902 3.48991C19.7002 2.21991 21.7702 4.29991 20.5102 8.10991L17.6802 16.5999C15.7802 22.3099 12.6602 22.3099 10.7602 16.5999L9.92018 14.0799L7.40018 13.2399C1.69018 11.3399 1.69018 8.22991 7.40018 6.31991Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M10.1099 13.6501L13.6899 10.0601"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  agent: (
    <>
      <path
        d="M17.29 4.13999L17.22 7.92997C17.21 8.44997 17.54 9.13999 17.96 9.44999L20.44 11.33C22.03 12.53 21.77 14 19.87 14.6L16.64 15.61C16.1 15.78 15.53 16.37 15.39 16.92L14.62 19.86C14.01 22.18 12.49 22.41 11.23 20.37L9.46999 17.52C9.14999 17 8.39 16.61 7.79 16.64L4.45003 16.81C2.06003 16.93 1.38002 15.55 2.94002 13.73L4.92 11.43C5.29 11 5.46 10.2 5.29 9.65998L4.28005 6.42997C3.69005 4.52997 4.75004 3.47999 6.64004 4.09999L9.59005 5.06999C10.09 5.22999 10.84 5.11998 11.26 4.80998L14.34 2.58998C16 1.38998 17.33 2.08999 17.29 4.13999Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M21.91 22L18.88 18.97"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  sun: (
    <>
      <path
        d="M18.5 12C18.5 15.5899 15.5899 18.5 12 18.5C8.41015 18.5 5.5 15.5899 5.5 12C5.5 8.41015 8.41015 5.5 12 5.5C15.5899 5.5 18.5 8.41015 18.5 12Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M19.14 19.14L19.01 19.01M19.01 4.99L19.14 4.86L19.01 4.99ZM4.86 19.14L4.99 19.01L4.86 19.14ZM12 2.08V2V2.08ZM12 22V21.92V22ZM2.08 12H2H2.08ZM22 12H21.92H22ZM4.99 4.99L4.86 4.86L4.99 4.99Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  moon: (
    <>
      <path
        d="M2.03009 12.42C2.39009 17.57 6.76009 21.76 11.9901 21.99C15.6801 22.15 18.9801 20.43 20.9601 17.72C21.7801 16.61 21.3401 15.87 19.9701 16.12C19.3001 16.24 18.6101 16.29 17.8901 16.26C13.0001 16.06 9.00009 11.97 8.98009 7.14002C8.97009 5.84002 9.24009 4.61002 9.73009 3.49002C10.2701 2.25002 9.62009 1.66002 8.37009 2.19002C4.41009 3.86002 1.70009 7.85002 2.03009 12.42Z"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  loader: (
    <>
      <path
        d="M14.89 5.08002C14.02 4.82002 13.06 4.65002 12 4.65002C7.20996 4.65002 3.32996 8.53002 3.32996 13.32C3.32996 18.12 7.20996 22 12 22C16.79 22 20.67 18.12 20.67 13.33C20.67 11.55 20.13 9.89002 19.21 8.51002"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M16.13 5.32L13.24 2"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M16.13 5.31995L12.76 7.77995"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  zoomIn: (
    <>
      <path
        d="M6 12H18"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M12 18V6"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  zoomOut: (
    <>
      <path
        d="M6 12H18"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  fit: (
    <>
      <path
        d="M21 9V3H15"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M3 15V21H9"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M21 3L13.5 10.5"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M10.5 13.5L3 21"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
  brand: (
    <>
      <path
        d="M8.96997 5.5C8.96997 7.433 7.40297 9 5.46997 9C3.53697 9 1.96997 7.433 1.96997 5.5C1.96997 3.567 3.53697 2 5.46997 2C7.40297 2 8.96997 3.567 8.96997 5.5Z"
        strokeWidth="1.5"
        stroke="currentColor"
      />
      <path
        d="M16.97 15H19.97C21.07 15 21.97 15.9 21.97 17V20C21.97 21.1 21.07 22 19.97 22H16.97C15.87 22 14.97 21.1 14.97 20V17C14.97 15.9 15.87 15 16.97 15Z"
        strokeWidth="1.5"
        stroke="currentColor"
      />
      <path
        d="M11.9999 5H14.6799C16.5299 5 17.3899 7.29 15.9999 8.51L8.00995 15.5C6.61995 16.71 7.47994 19 9.31994 19H11.9999"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M5.48622 5.5H5.49777"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
      <path
        d="M18.4862 18.5H18.4978"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        stroke="currentColor"
      />
    </>
  ),
};

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 16, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {SHAPES[name]}
    </svg>
  );
}
