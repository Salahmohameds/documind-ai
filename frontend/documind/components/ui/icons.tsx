import type { CSSProperties, ReactNode } from "react";

type IconProps = {
  size?: number;
  color?: string;
  strokeWidth?: number;
  style?: CSSProperties;
};

function Svg({
  size = 16,
  color = "currentColor",
  strokeWidth = 1.7,
  style,
  children,
}: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ width: size, height: size, flex: "none", ...style }}
      aria-hidden
    >
      {children}
    </svg>
  );
}

export const GridIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
  </Svg>
);

export const UploadIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 15.5V4" />
    <path d="M7.5 8.5 12 4l4.5 4.5" />
    <path d="M4 16v3.5h16V16" />
  </Svg>
);

export const FileIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M13.5 3.5H8A1.5 1.5 0 0 0 6.5 5v14A1.5 1.5 0 0 0 8 20.5h8a1.5 1.5 0 0 0 1.5-1.5V7.5z" />
    <path d="M13.5 3.5v4h4" />
  </Svg>
);

export const BoltIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M13 3 5.5 13.5H11l-1 7.5 8-11h-5.5z" />
  </Svg>
);

export const MoonIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z" />
  </Svg>
);

export const GearIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 3.5v2M12 18.5v2M4.5 12h2M17.5 12h2M6.7 6.7l1.4 1.4M15.9 15.9l1.4 1.4M17.3 6.7l-1.4 1.4M8.1 15.9l-1.4 1.4" />
  </Svg>
);

export const TeamIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="9.5" cy="9" r="3.2" />
    <path d="M4 19.5c0-2.8 2.5-4.5 5.5-4.5s5.5 1.7 5.5 4.5" />
    <path d="M16 6.6a3.2 3.2 0 0 1 0 6.3" />
    <path d="M17.5 15.4c1.7.6 2.5 2.1 2.5 4.1" />
  </Svg>
);

export const SignOutIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M15 5.5H6.5v13H15" />
    <path d="M12 12h8" />
    <path d="M17 9l3 3-3 3" />
  </Svg>
);

export const ChevronUpIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 14l5-5 5 5" />
  </Svg>
);

export const ChevronDownIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 9.5l6 6 6-6" />
  </Svg>
);

export const CaretDownIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6 10l6 6 6-6" />
  </Svg>
);

export const SearchIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.4-4.4" />
  </Svg>
);

export const BellIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M6.5 10a5.5 5.5 0 0 1 11 0v4l1.5 2.5h-14L6.5 14z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </Svg>
);

export const SunIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.5 1.5M16.9 16.9l1.5 1.5M18.4 5.6l-1.5 1.5M7.1 16.9l-1.5 1.5" />
  </Svg>
);

export const CalendarIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="5.5" width="16" height="14" rx="2.5" />
    <path d="M8 3.5v3M16 3.5v3M4 10h16" />
  </Svg>
);

export const PlusIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);

export const DownloadIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 4v10" />
    <path d="M8 10.5l4 3.5 4-3.5" />
    <path d="M5 19h14" />
  </Svg>
);

export const BarsIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M5 19.5V12" />
    <path d="M12 19.5V5" />
    <path d="M19 19.5v-5" />
  </Svg>
);

export const WarningIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 4l8.5 15.5H3.5z" />
    <path d="M12 10v4" />
    <path d="M12 17h.01" />
  </Svg>
);

export const ShieldIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 3.5l7 2.7V12c0 4-2.9 7-7 8.3C7.9 19 5 16 5 12V6.2z" />
    <path d="M12 9v3.5" />
    <path d="M12 15.5h.01" />
  </Svg>
);

export const ClockIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8" />
    <path d="M12 7.5V12l3 1.8" />
  </Svg>
);

export const TrendUpIcon = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <path d="M12 19V6" />
    <path d="M6.5 11.5 12 6l5.5 5.5" />
  </Svg>
);

export const TrendDownIcon = (p: IconProps) => (
  <Svg strokeWidth={2.2} {...p}>
    <path d="M12 5v13" />
    <path d="M6.5 12.5 12 18l5.5-5.5" />
  </Svg>
);

export const RefreshIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M19.5 12a7.5 7.5 0 1 1-2.6-5.7" />
    <path d="M19.5 4.5V8h-3.5" />
  </Svg>
);

export const ChatIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M20 12.5c0 3.6-3.6 6.5-8 6.5-1 0-2-.2-2.9-.5L5 20l1.2-3.2A6.2 6.2 0 0 1 4 12.5C4 8.9 7.6 6 12 6s8 2.9 8 6.5z" />
  </Svg>
);

export const LockIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="5" y="10.5" width="14" height="9.5" rx="2.5" />
    <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
  </Svg>
);

export const CloudUploadIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 17.5a4 4 0 0 1 .4-8A5.5 5.5 0 0 1 18 10.6a3.5 3.5 0 0 1-.5 6.9" />
    <path d="M12 20v-8" />
    <path d="M9 14.5 12 11.5l3 3" />
  </Svg>
);

export const ArrowLeftIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M19 12H5" />
    <path d="M11 6l-6 6 6 6" />
  </Svg>
);

export const KebabIcon = ({ size = 18, color = "currentColor", style }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    style={{ width: size, height: size, flex: "none", ...style }}
    aria-hidden
  >
    <circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" />
  </svg>
);

/* -- Search palette ------------------------------------------------------ */

/** A clause or heading inside a document. */
export const HashIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M10 3 8 21M16 3l-2 18M3.5 8.5h17M3 15.5h17" />
  </Svg>
);

/** An extracted key/value pair. */
export const TagIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9-9-9Z" />
    <circle cx="7.5" cy="7.5" r="1.4" />
  </Svg>
);

/** The return key, for the keyboard footer. */
export const ReturnIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M9 10 5 14l4 4" />
    <path d="M5 14h10a4 4 0 0 0 4-4V6" />
  </Svg>
);
