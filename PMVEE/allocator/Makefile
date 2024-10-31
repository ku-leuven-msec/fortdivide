all: pmvee_allocator.c
	clang -O3                  -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator.so pmvee_allocator.c
	clang -O3 -DPMVEE_LEADER   -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator_l.so pmvee_allocator.c
	clang -O3 -DPMVEE_FOLLOWER -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator_f.so pmvee_allocator.c

debug: pmvee_allocator.c
	clang -g                  -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator.so pmvee_allocator.c
	clang -g -DPMVEE_LEADER   -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator_l.so pmvee_allocator.c
	clang -g -DPMVEE_FOLLOWER -I../PMVEE/ \
		-lc -fPIC -shared -o pmvee_allocator_f.so pmvee_allocator.c

clean:
	rm pmvee_allocator.so
	rm pmvee_allocator_l.so
	rm pmvee_allocator_f.so