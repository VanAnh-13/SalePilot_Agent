// Shared inline SVG icon set — replaces emoji across the app so glyphs render
// identically on every OS/browser instead of relying on platform emoji fonts.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    ...props,
  };
}

export function IconCart(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="9" cy="20" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="18" cy="20" r="1.4" fill="currentColor" stroke="none" />
      <path d="M2.5 3h2l2.2 11.4a2 2 0 0 0 2 1.6h8.1a2 2 0 0 0 2-1.6L21 7H6" />
    </svg>
  );
}

export function IconSun(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.5v2.4M12 19.1v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7" />
    </svg>
  );
}

export function IconMoon(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M20.5 14.2A8.5 8.5 0 1 1 9.8 3.5a7 7 0 0 0 10.7 10.7Z" />
    </svg>
  );
}

export function IconTarget(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="8.2" />
      <circle cx="12" cy="12" r="4.4" />
      <circle cx="12" cy="12" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconScale(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3v17.5M8.2 20.5h7.6" />
      <path d="M5 7.5h4.6M14.4 7.5H19" />
      <path d="M5 7.5 2.6 12.6a2.6 2.6 0 0 0 4.8 0L5 7.5ZM19 7.5l-2.4 5.1a2.6 2.6 0 0 0 4.8 0L19 7.5Z" />
    </svg>
  );
}

export function IconSearchCheck(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="10.5" cy="10.5" r="6.8" />
      <path d="m20.5 20.5-4.4-4.4M7.7 10.6l1.8 1.9 3.3-3.6" />
    </svg>
  );
}

export function IconShield(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 2.8 19.5 6v6.2c0 4.6-3.1 7.9-7.5 9-4.4-1.1-7.5-4.4-7.5-9V6L12 2.8Z" />
      <path d="m9 12 2.1 2.1L15.3 10" />
    </svg>
  );
}

export function IconBot(props: IconProps) {
  return (
    <svg {...base(props)}>
      <rect x="4" y="8.5" width="16" height="10.5" rx="3.2" />
      <path d="M12 8.5V5.2M9.4 4.2h5.2" />
      <circle cx="9" cy="13.6" r="1.15" fill="currentColor" stroke="none" />
      <circle cx="15" cy="13.6" r="1.15" fill="currentColor" stroke="none" />
      <path d="M9.4 17h5.2" />
      <path d="M2.6 12.5v3M21.4 12.5v3" />
    </svg>
  );
}

export function IconUser(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.8 20.2a7.2 7.2 0 0 1 14.4 0" />
    </svg>
  );
}

export function IconSend(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M21 3 3 10.6l7 2.6 2.6 7L21 3Z" />
      <path d="M21 3 12.6 13.2" />
    </svg>
  );
}

export function IconAlert(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3.2 22 20.5H2L12 3.2Z" />
      <path d="M12 9.6v4.6" />
      <circle cx="12" cy="17.3" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconRefresh(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M20 11a8 8 0 0 0-14.5-4.6M4 13a8 8 0 0 0 14.5 4.6" />
      <path d="M20 4v4.4h-4.4M4 20v-4.4h4.4" />
    </svg>
  );
}

export function IconUsers(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="9" cy="8.2" r="3.1" />
      <path d="M3.4 19.5a5.7 5.7 0 0 1 11.2 0" />
      <path d="M16 5.3a3.1 3.1 0 0 1 0 6M18.7 19.5a5.7 5.7 0 0 0-3.4-5.4" />
    </svg>
  );
}

export function IconChat(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M4 5.5h16v10.6H9.6L5 20V16.1H4Z" />
      <path d="M8 9.6h8M8 12.6h5" />
    </svg>
  );
}

export function IconBrain(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M9.5 3.6a2.9 2.9 0 0 0-2.9 2.9v.4A2.9 2.9 0 0 0 4.9 9.7a2.9 2.9 0 0 0 0 4.6 2.9 2.9 0 0 0 1.7 3.9v.3a2.9 2.9 0 0 0 5.4 1.5" />
      <path d="M14.5 3.6a2.9 2.9 0 0 1 2.9 2.9v.4a2.9 2.9 0 0 1 1.7 2.8 2.9 2.9 0 0 1 0 4.6 2.9 2.9 0 0 1-1.7 3.9v.3a2.9 2.9 0 0 1-5.4 1.5" />
      <path d="M12 4v16" />
    </svg>
  );
}

export function IconClock(props: IconProps) {
  return (
    <svg {...base(props)}>
      <circle cx="12" cy="12" r="8.4" />
      <path d="M12 7.4V12l3.2 2" />
    </svg>
  );
}

export function IconHash(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M9.5 3.5 7 20.5M17 3.5l-2.5 17M4 8.7h16M3 15.3h16" />
    </svg>
  );
}

export function IconLayers(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="m12 3 8.5 4.9L12 12.8 3.5 7.9 12 3Z" />
      <path d="m3.5 12 8.5 4.9 8.5-4.9M3.5 16.1 12 21l8.5-4.9" />
    </svg>
  );
}

export function IconSparkle(props: IconProps) {
  return (
    <svg {...base(props)}>
      <path d="M12 3.5 13.6 9l5.4 1.6-5.4 1.6L12 17.7l-1.6-5.5L5 10.6 10.4 9 12 3.5Z" />
      <path d="M19 15.5 19.7 18 22 18.7 19.7 19.4 19 22l-.7-2.6-2.3-.7 2.3-.7.7-2.5Z" />
    </svg>
  );
}
