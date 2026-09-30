#ifndef PHOTO_SCROLL_H
#define PHOTO_SCROLL_H
#include <math.h>
#include <stdbool.h>
/* Invert the renderer's center rotation and horizontal reflection. */
static inline bool photo_contains(double x, double y, double left, double top,
    double width, double height, double rotation, bool mirrored)
{
  if (width <= 0 || height <= 0) return false;
  double dx = x - (int)(left + width / 2);
  const double dy = y - (int)(top + height / 2);
  if (mirrored) dx = -dx;
  const double angle = rotation * 0.017453292519943295;
  const double local_x = cos(angle) * dx + sin(angle) * dy;
  const double local_y = -sin(angle) * dx + cos(angle) * dy;
  return fabs(local_x) <= width / 2 && fabs(local_y) <= height / 2;
}
#endif
