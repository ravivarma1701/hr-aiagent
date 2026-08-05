import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const authCookie = request.cookies.get("hrms_auth")?.value;
  const { pathname } = request.nextUrl;

  const isEmployeesRoute = pathname.startsWith("/employees");
  const isDashboardRoute = pathname.startsWith("/dashboard");
  const isAttendanceRoute = pathname.startsWith("/attendance");
  const isLeavesRoute = pathname.startsWith("/leaves");
  const isAnnouncementsRoute = pathname.startsWith("/announcements");
  const isTeamCalendarRoute = pathname.startsWith("/team-calendar");
  const isMeRoute = pathname.startsWith("/me");
  const isFinanceRoute = pathname.startsWith("/finance");
  const isTicketsRoute = pathname.startsWith("/tickets");
  const isPollsRoute = pathname.startsWith("/polls");
  const isHRPoliciesRoute = pathname.startsWith("/hr-policies");
  const isLoginRoute = pathname === "/login";

  if (
    (isEmployeesRoute ||
      isDashboardRoute ||
      isMeRoute ||
      isFinanceRoute ||
      isAttendanceRoute ||
      isLeavesRoute ||
      isAnnouncementsRoute ||
      isHRPoliciesRoute ||
      isPollsRoute ||
      isTeamCalendarRoute ||
      isTicketsRoute) &&
    !authCookie
  ) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (isLoginRoute && authCookie) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/dashboard/:path*",
    "/employees/:path*",
    "/me/:path*",
    "/finance/:path*",
    "/attendance/:path*",
    "/leaves/:path*",
    "/announcements/:path*",
    "/hr-policies/:path*",
    "/polls/:path*",
    "/team-calendar/:path*",
    "/tickets/:path*",
  ],
};
