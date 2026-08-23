# Stage 1: Build the React application
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build the production assets
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
# Overwrite default Nginx config with our custom proxy routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy the compiled React files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]