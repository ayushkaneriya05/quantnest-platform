import axiosInstance from "./api";

const BASE_URL = "/market";

export const marketApi = {
  getLiveQuote: (instrument) =>
    axiosInstance.get(`${BASE_URL}/live/quote/`, { params: { instrument } }),
  getLiveIndices: () => axiosInstance.get(`${BASE_URL}/live/indices/`),
  getEvents: (params) => axiosInstance.get(`${BASE_URL}/events/`, { params }),
};

export default marketApi;
