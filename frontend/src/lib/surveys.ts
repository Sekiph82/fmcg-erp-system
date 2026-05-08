import { apiClient } from "@/lib/api";

const BASE = "/api/v1/surveys";

export type SurveyType = "PULSE" | "ENGAGEMENT" | "EXIT" | "ONBOARDING" | "CUSTOM";
export type SurveyStatus = "DRAFT" | "ACTIVE" | "CLOSED" | "ARCHIVED";
export type QuestionType = "RATING" | "NPS" | "MULTIPLE_CHOICE" | "TEXT" | "YES_NO" | "LIKERT";

export interface SurveyQuestion {
  id: string;
  question_text: string;
  question_type: QuestionType;
  required_flag: boolean;
  display_order: number;
  options?: string[];
  scale_min?: number;
  scale_max?: number;
  category?: string;
}

export interface Survey {
  id: string;
  title: string;
  description?: string;
  survey_type: SurveyType;
  status: SurveyStatus;
  anonymous_flag: boolean;
  start_date?: string;
  end_date?: string;
  target_department?: string;
  target_all: boolean;
  question_count: number;
  response_count: number;
  is_open: boolean;
  created_at: string;
}

export interface SurveyDetail extends Omit<Survey, "question_count"> {
  questions: SurveyQuestion[];
  created_by_name?: string;
}

export interface QuestionStat {
  question_id: string;
  question_text: string;
  question_type: QuestionType;
  category?: string;
  answer_count: number;
  avg?: number;
  min?: number;
  max?: number;
  distribution?: Record<string, number>;
  sample_responses?: string[];
}

export interface SurveyResults {
  survey_id: string;
  title: string;
  survey_type: SurveyType;
  total_responses: number;
  engagement_score?: number;
  questions: QuestionStat[];
}

export interface SurveyDashboard {
  total_surveys: number;
  active_surveys: number;
  closed_surveys: number;
  total_responses: number;
  active_surveys_list: { id: string; title: string; survey_type: string; end_date?: string; response_count: number }[];
}

export const surveysApi = {
  listSurveys: (params?: { status?: SurveyStatus; survey_type?: SurveyType }) =>
    apiClient.get<Survey[]>(BASE + "/", { params }).then(r => r.data),
  getSurvey: (id: string) =>
    apiClient.get<SurveyDetail>(`${BASE}/${id}`).then(r => r.data),
  createSurvey: (data: object) =>
    apiClient.post<{ id: string; title: string; status: string }>(BASE + "/", data).then(r => r.data),
  updateSurvey: (id: string, data: object) =>
    apiClient.patch<{ id: string; status: string }>(`${BASE}/${id}`, data).then(r => r.data),
  launchSurvey: (id: string) =>
    apiClient.post<{ id: string; status: string }>(`${BASE}/${id}/launch`).then(r => r.data),
  closeSurvey: (id: string) =>
    apiClient.post<{ id: string; status: string }>(`${BASE}/${id}/close`).then(r => r.data),

  addQuestion: (surveyId: string, data: object) =>
    apiClient.post<{ id: string }>(`${BASE}/${surveyId}/questions`, data).then(r => r.data),
  deleteQuestion: (surveyId: string, questionId: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/${surveyId}/questions/${questionId}`).then(r => r.data),

  submitResponse: (surveyId: string, answers: Record<string, unknown>) =>
    apiClient.post<{ id: string; completion_pct: number }>(`${BASE}/${surveyId}/respond`, { answers }).then(r => r.data),

  getResults: (id: string) =>
    apiClient.get<SurveyResults>(`${BASE}/${id}/results`).then(r => r.data),
  getDashboard: () =>
    apiClient.get<SurveyDashboard>(`${BASE}/dashboard/stats`).then(r => r.data),
};

export const SURVEY_TYPE_LABEL: Record<SurveyType, string> = {
  PULSE: "Pulse Survey", ENGAGEMENT: "Engagement Survey",
  EXIT: "Exit Interview", ONBOARDING: "Onboarding Survey", CUSTOM: "Custom Survey",
};

export const QUESTION_TYPE_LABEL: Record<QuestionType, string> = {
  RATING: "Rating (1-5)", NPS: "NPS (0-10)",
  MULTIPLE_CHOICE: "Multiple Choice", TEXT: "Free Text",
  YES_NO: "Yes / No", LIKERT: "Likert Scale",
};
