import React from "react";

function Icon({ children }) {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function ActivityIcon() {
  return (
    <Icon>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M13 10V3L4 14h7v7l9-11h-7z"
      />
    </Icon>
  );
}

export function ServerIcon() {
  return (
    <Icon>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
      />
    </Icon>
  );
}

export function ClockIcon() {
  return (
    <Icon>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </Icon>
  );
}

export function PlayIcon() {
  return (
    <Icon>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M14.75 11.17l-3.2-2.13A1 1 0 0010 9.87v4.26a1 1 0 001.55.83l3.2-2.13a1 1 0 000-1.66z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </Icon>
  );
}

export function StopIcon() {
  return (
    <Icon>
      <path strokeWidth="2" d="M7 7h10v10H7z" />
      <circle cx="12" cy="12" r="9" strokeWidth="2" />
    </Icon>
  );
}

export function CloseIcon() {
  return (
    <Icon>
      <path d="M6 6l12 12M18 6L6 18" strokeWidth="2" strokeLinecap="round" />
    </Icon>
  );
}
