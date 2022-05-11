FROM node:alpine
WORKDIR /app
COPY ./backend /app
COPY ./client/build /app/build
EXPOSE 5000
RUN yarn install
CMD ["yarn", "run", "start"]