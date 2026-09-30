#include "src/photo_scroll.h"
#include <assert.h>
int main(void) {
  assert(photo_contains(150,100,100,50,200,100,0,false));
  assert(!photo_contains(99,100,100,50,200,100,0,false));
  assert(!photo_contains(301,100,100,50,200,100,0,false));
  assert(!photo_contains(200,49,100,50,200,100,0,false));
  assert(!photo_contains(200,151,100,50,200,100,0,false));
  assert(photo_contains(200,190,100,50,200,100,90,false));
  assert(!photo_contains(290,100,100,50,200,100,90,false));
  assert(photo_contains(270,170,100,50,200,100,45,false));
  assert(!photo_contains(270,30,100,50,200,100,45,false));
  assert(photo_contains(130,170,100,50,200,100,45,true));
  assert(!photo_contains(130,30,100,50,200,100,45,true));
  assert(photo_contains(0,0,-500,-500,2000,1500,0,false));
  assert(!photo_contains(0,0,0,0,0,0,0,false));
  return 0;
}
