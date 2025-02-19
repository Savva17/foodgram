# build env
FROM node:21.7.1-alpine
WORKDIR /app
# COPY package*.json ./
COPY package.json package.json
COPY package-lock.json package-lock.json
RUN npm install
COPY . .
RUN npm run build
RUN npm install --global http-server
# CMD cp -r build result_build
CMD ["npx", "-y", "http-server", "-p", "8888", "/app/build"]
