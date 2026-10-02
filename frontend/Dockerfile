FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG BACKEND_URL=http://backend:8000
ARG NEXT_PUBLIC_BRAND_NAME=PolarNexus
ENV BACKEND_URL=$BACKEND_URL NEXT_PUBLIC_BRAND_NAME=$NEXT_PUBLIC_BRAND_NAME NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app ./
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
