# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS build
WORKDIR /app

# Install all dependencies, including dev, for the build step
ENV NODE_ENV=development

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
WORKDIR /usr/share/nginx/html

COPY --from=build /app/dist ./
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["/docker-entrypoint.sh", "nginx", "-g", "daemon off;"]
