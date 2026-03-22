FROM node:20-alpine

WORKDIR /app

COPY package.json ./package.json
COPY package-lock.json ./package-lock.json
COPY tsconfig.base.json ./tsconfig.base.json
COPY apps/web/package.json ./apps/web/package.json
COPY packages/shared/package.json ./packages/shared/package.json

WORKDIR /app
RUN npm ci

WORKDIR /app
COPY apps/web ./apps/web
COPY packages/shared ./packages/shared

WORKDIR /app/apps/web
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
