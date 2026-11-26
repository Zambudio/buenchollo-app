FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY src ./src
EXPOSE 3000
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s CMD wget -qO- http://127.0.0.1:3000/health >/dev/null || exit 1
CMD ["node", "src/server.js"]
