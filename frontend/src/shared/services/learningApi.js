import api from "@/shared/services/api";

export const learningApi = {
  getPaths: () => api.get("/learning/paths/"),
  getCourses: (params = {}) => api.get("/learning/courses/", { params }),
  getCourse: (slug) => api.get(`/learning/courses/${slug}/`),
  enrollCourse: (slug) => api.post(`/learning/courses/${slug}/enroll/`),
  getLessons: (params = {}) => api.get("/learning/lessons/", { params }),
  getLesson: (id) => api.get(`/learning/lessons/${id}/`),
  completeLesson: (id, payload = {}) => api.post(`/learning/lessons/${id}/complete/`, payload),
  getProgress: () => api.get("/learning/progress/"),
  getQuizzes: () => api.get("/learning/quizzes/"),
  submitQuiz: (id, answers) => api.post(`/learning/quizzes/${id}/submit/`, { answers }),
  getAssignments: () => api.get("/learning/assignments/"),
  submitAssignment: (id, payload) => api.post(`/learning/assignments/${id}/submit/`, payload),
  getCertificates: () => api.get("/learning/certificates/"),
  getRecommendations: () => api.get("/learning/recommendations/"),
  createSignal: (payload) => api.post("/learning/signals/", payload),
};

