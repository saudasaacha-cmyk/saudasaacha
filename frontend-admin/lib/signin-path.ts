"use client";

import { STORAGE_KEYS } from "@/lib/constants";

/**
 * Which sign-in screen this browser belongs to.
 *
 * There are two portals on the same host — `/login` for admin-tier
 * accounts and `/employee-login` for staff — and every redirect out of
 * the app used to hardcode the first one. So an employee who signed out
 * (or whose session expired) landed on the Admin Login form, which their
 * credentials are rejected by: the backend only accepts role == EMPLOYEE
 * at the employee endpoint. They had no way back in without being told
 * the URL.
 *
 * The portal is remembered at sign-in and deliberately NOT cleared on
 * logout — remembering it is the entire point.
 */
export type Portal = "admin" | "employee";

export const ADMIN_LOGIN_PATH = "/login";
export const EMPLOYEE_LOGIN_PATH = "/employee-login";

export function rememberPortal(portal: Portal): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEYS.lastPortal, portal);
  } catch {
    // Private mode / storage full — signInPath() falls back to /login.
  }
}

/** The sign-in screen to send this browser back to. */
export function signInPath(): string {
  if (typeof window === "undefined") return ADMIN_LOGIN_PATH;
  try {
    return window.localStorage.getItem(STORAGE_KEYS.lastPortal) === "employee"
      ? EMPLOYEE_LOGIN_PATH
      : ADMIN_LOGIN_PATH;
  } catch {
    return ADMIN_LOGIN_PATH;
  }
}

/** True when the given path already IS one of the sign-in screens, so a
 *  401 on the login form itself doesn't bounce the page to itself. */
export function isSignInPath(pathname: string): boolean {
  return (
    pathname === ADMIN_LOGIN_PATH ||
    pathname.startsWith(ADMIN_LOGIN_PATH + "/") ||
    pathname === EMPLOYEE_LOGIN_PATH ||
    pathname.startsWith(EMPLOYEE_LOGIN_PATH + "/")
  );
}
