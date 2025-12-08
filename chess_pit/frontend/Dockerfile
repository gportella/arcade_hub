# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS build
WORKDIR /app

ENV NODE_ENV=development

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_CHESS_API_BASE=http://localhost:8000
ARG VITE_CHESS_WS_BASE=http://localhost:8000
ARG VITE_BASE_PATH=/
ENV VITE_CHESS_API_BASE=${VITE_CHESS_API_BASE}
ENV VITE_CHESS_WS_BASE=${VITE_CHESS_WS_BASE}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
WORKDIR /usr/share/nginx/html

COPY --from=build /app/dist ./
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["/docker-entrypoint.sh", "nginx", "-g", "daemon off;"]
