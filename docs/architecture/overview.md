# Backend Architecture

## Overview

The backend follows a layered architecture:

``` text
Client / Frontend
       |
       v
REST API / Router
       |
       v
BaseAPIView
       |
       +---- Permissions
       +---- Multi-tenancy
       +---- Search/Filters
       |
       v
Serializer
       |
       v
Model
       |
       v
Database
```

## Responsibilities

### View

Receives the request, determines the action, restricts the queryset and
coordinates the serializer and the response.

### Serializer

Validates input data and turns Django instances into data suitable for the
API.

### Model

Represents persistent data and domain relationships.

### Base components

The framework concentrates repeated behavior into shared classes and
utilities so that each application doesn't reimplement CRUD, tenancy,
permissions and representation from scratch.
