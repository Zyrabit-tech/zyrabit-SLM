FROM node:20-alpine

WORKDIR /site
COPY package.json ./
RUN npm install

COPY . .
EXPOSE 3001
CMD ["npm", "run", "start"]
