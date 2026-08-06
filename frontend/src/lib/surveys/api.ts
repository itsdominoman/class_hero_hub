import { api } from "$lib/api";
import type { SessionMembership } from "$lib/roleRouting";

export type SurveyMembership = SessionMembership;

function headers(membership: SurveyMembership): Record<string, string> {
  return {
    "X-School-Id": String(membership.school_id),
    "X-Membership-Id": String(membership.membership_id),
  };
}

export const surveyApi = {
  availability: (membership: SurveyMembership) =>
    api.get("/school/surveys/availability", { headers: headers(membership) }),
  context: (membership: SurveyMembership) =>
    api.get("/school/surveys/context", { headers: headers(membership) }),
  list: (membership: SurveyMembership) =>
    api.get("/school/surveys", { headers: headers(membership) }),
  create: (membership: SurveyMembership, body: any) =>
    api.post("/school/surveys", body, { headers: headers(membership) }),
  update: (membership: SurveyMembership, id: string, body: any) =>
    api.put(`/school/surveys/${id}`, body, { headers: headers(membership) }),
  detail: (membership: SurveyMembership, id: string) =>
    api.get(`/school/surveys/${id}`, { headers: headers(membership) }),
  results: (membership: SurveyMembership, id: string, q = "", page = 1) =>
    api.get(
      `/school/surveys/${id}/results?q=${encodeURIComponent(q)}&page=${page}`,
      { headers: headers(membership) },
    ),
  action: (
    membership: SurveyMembership,
    id: string,
    action: string,
    body: Record<string, unknown> = {},
  ) =>
    api.post(
      `/school/surveys/${id}/${action}`,
      body,
      { headers: headers(membership) },
    ),
  exportCsv: (membership: SurveyMembership, id: string) =>
    api.download(`/school/surveys/${id}/export.csv`, {
      headers: headers(membership),
      cache: "no-store",
    }),
  generatedSummary: (membership: SurveyMembership, id: string, language: "en" | "ar") =>
    api.post(`/school/surveys/${id}/generated-summary`, { language }, {
      headers: headers(membership),
    }),
  permissions: (membership: SurveyMembership) =>
    api.get("/school/surveys/permissions", { headers: headers(membership) }),
  setPermission: (membership: SurveyMembership, body: any) =>
    api.post("/school/surveys/permissions", body, {
      headers: headers(membership),
    }),
};
