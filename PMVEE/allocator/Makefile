all: pmvee_allocator.c
	clang -O3                  -I../ \
		-lc -fPIC -shared -o pmvee_allocator.so pmvee_allocator.c
	clang -O3 -DPMVEE_LEADER   -I../ \
		-lc -fPIC -shared -o pmvee_allocator_l.so pmvee_allocator.c
	clang -O3 -DPMVEE_FOLLOWER -I../ \
		-lc -fPIC -shared -o pmvee_allocator_f.so pmvee_allocator.c

debug: pmvee_allocator.c
	clang -g                  -I../ \
		-lc -fPIC -shared -o pmvee_allocator.so pmvee_allocator.c
	clang -g -DPMVEE_LEADER   -I../ \
		-lc -fPIC -shared -o pmvee_allocator_l.so pmvee_allocator.c
	clang -g -DPMVEE_FOLLOWER -I../ \
		-lc -fPIC -shared -o pmvee_allocator_f.so pmvee_allocator.c

clean:
	rm pmvee_allocator.so
	rm pmvee_allocator_l.so
	rm pmvee_allocator_f.so