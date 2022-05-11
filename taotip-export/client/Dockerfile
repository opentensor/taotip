FROM node:alpine
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
COPY ./ ./
EXPOSE 3000
RUN yarn install
CMD ["yarn", "run", "start"]