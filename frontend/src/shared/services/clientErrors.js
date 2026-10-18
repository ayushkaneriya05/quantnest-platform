import api from './api';

export function reportClientError(category) {
  api.post('/support/client-errors/', {category}).catch(() => {});
}
