FROM node:20-alpine AS build
WORKDIR /app
# v0.10 follow-up: empty by default -- api.ts treats "" as "same origin,
# relative /api/... path", which nginx.conf now proxies to the backend
# container. Only set this if you truly need to point the built frontend at
# a *different* host than the one serving it (unusual).
ARG VITE_API_BASE=
ENV VITE_API_BASE=$VITE_API_BASE
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
