# Notifications

User notifications (list, get, mark read, mark all read). Scoped to the authenticated user.

## Endpoints

| Method | Path                               | Description                                                      |
| ------ | ---------------------------------- | ---------------------------------------------------------------- |
| GET    | `/api/notifications`               | List user's notifications (query: `unread=true` for unread only) |
| GET    | `/api/notifications/:id`           | Get notification by id                                           |
| POST   | `/api/notifications/mark-all-read` | Mark all as read                                                 |
| POST   | `/api/notifications/:id/read`      | Mark one as read                                                 |

## Dependencies

- **Models:** `Notification` from `src/models`
- **Shared:** `lib/params`, `lib/pagination`, `middleware/asyncHandler`
