FROM node:alpine
WORKDIR /app
COPY package.json ./
COPY package-lock.json ./
COPY ./ ./
EXPOSE 5000
RUN yarn install
CMD ["yarn", "run", "start"]