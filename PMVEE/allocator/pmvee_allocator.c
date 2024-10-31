#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <assert.h>
#include <string.h>

#if defined(PMVEE_LEADER) || defined(PMVEE_FOLLOWER)
#include "PMVEE.h"
#else
#define MAP_PMVEE 0x00
#endif

#define DEFAULT_AREA_SIZE 0x1000 * 16
#define ROUND_UP(x, multiple)   ( (((long long)(x)) + multiple-1)  & (~(multiple-1)) )


#define HIGHEST_BIT 1l << 63

#define raw_exit(code) asm("syscall;" :: "a" (231), "D" (code));


struct allocation_t
{
    struct allocation_t* next;
    struct allocation_t* prev;
    unsigned long size;
};


struct alloc_area_t
{
    struct alloc_area_t* next_area;
    struct alloc_area_t* prev_area;
    struct allocation_t* next_free;
    struct allocation_t* last_full;
    unsigned long area_size;
    void* area;
};


static struct alloc_area_t* head_area = (struct alloc_area_t*)0x00;
static struct alloc_area_t* last_area = (struct alloc_area_t*)0x00;


struct alloc_area_t* new_alloc_area(struct alloc_area_t*, size_t);


void init_heap()
{
    head_area = new_alloc_area((struct alloc_area_t*)0x00, DEFAULT_AREA_SIZE);
    last_area = head_area;
}


struct alloc_area_t* new_alloc_area(struct alloc_area_t* old_alloc_area, size_t size)
{
    size_t page_size = ROUND_UP(sizeof(struct alloc_area_t) + sizeof(struct allocation_t) + size, 0x1000l);
    size = page_size - sizeof(struct alloc_area_t) - sizeof(struct allocation_t);
    void* created_alloc_area = mmap(0, page_size, PROT_READ | PROT_WRITE, MAP_ANON | MAP_PRIVATE | MAP_PMVEE, -1, 0);
    if (created_alloc_area == MAP_FAILED)
        raw_exit(42);
    struct alloc_area_t* alloc_area_meta = created_alloc_area + page_size - sizeof(struct alloc_area_t);
    *(alloc_area_meta) = (struct alloc_area_t)
    {
        .next_area = old_alloc_area ? old_alloc_area->next_area : (struct alloc_area_t*)0x00,
        .prev_area = old_alloc_area,
        .next_free = (struct allocation_t*) (((void*)alloc_area_meta) - sizeof(struct allocation_t)),
        .last_full = (struct allocation_t*)0x00,
        .area_size = size,
        .area = created_alloc_area
    };
    if (old_alloc_area)
    {
        if (old_alloc_area->next_area)
            old_alloc_area->next_area->prev_area = alloc_area_meta;
        old_alloc_area->next_area = alloc_area_meta;
    }
    *alloc_area_meta->next_free = (struct allocation_t)
    {
        .next = (struct allocation_t*)0x00,
        .prev = (struct allocation_t*)0x00,
        .size = size
    };
    return alloc_area_meta;
}


static void defragment_area(struct alloc_area_t* area)
{
    struct allocation_t* sorted;
    struct allocation_t* allocation_i = area->next_free;
    while (allocation_i)
    {
        sorted = allocation_i;
        for (struct allocation_t* sorted_i = allocation_i->next; sorted_i; sorted_i = sorted_i->next)
        {
            if (sorted_i < sorted)
                sorted = sorted_i;
        }
        if (sorted->prev)
            sorted->prev->next = sorted->next;
        if (sorted->next)
            sorted->next->prev = sorted->prev;
        if (allocation_i->prev)
            allocation_i->prev->next = sorted;
        sorted->prev = allocation_i->prev;
        sorted->next = allocation_i;
        allocation_i->prev = sorted;
    }
    while (sorted->prev)
        sorted = sorted->prev;
    area->next_free = sorted;
}


static void* do_allocate(struct alloc_area_t* area, struct allocation_t* next_free, size_t size)
{
    if ((next_free->size - size) >= (sizeof(struct allocation_t) + sizeof(unsigned long)))
    {
        struct allocation_t* new_free = (void*)next_free - sizeof(struct allocation_t) - size;
        *new_free = (struct allocation_t)
        {
            .next = next_free->next,
            .prev = next_free->prev,
            .size = next_free->size - size - sizeof(struct allocation_t)
        };
        if (area->next_free == next_free)
            area->next_free = new_free;
        next_free->size = size;
        if (next_free->next)
            next_free->next->prev = new_free;
        if (next_free->prev)
            next_free->prev->next = new_free;
    }
    else
    {
        if (next_free->next)
            next_free->next->prev = next_free->prev;
        if (next_free->prev)
            next_free->prev->next = next_free->next;
        if (area->next_free == next_free)
            area->next_free = next_free->next;
    }
    next_free->next = area->last_full;
    next_free->prev = (struct allocation_t*)0x00;
    if (area->last_full)
        area->last_full->prev = next_free;
    area->last_full = next_free;
    last_area = area;

    return (void*)(((void*)next_free) - next_free->size);
}


static void* do_allocate_lowest(struct alloc_area_t* area, struct allocation_t* next_free, size_t size)
{
    unsigned long leftover_size = next_free->size - size;
    if (leftover_size >= (sizeof(struct allocation_t) + sizeof(unsigned long)))
    {
        struct allocation_t* new_free = (void*)next_free - leftover_size;
        *new_free = (struct allocation_t)
        {
            .next = next_free,
            .prev = next_free->prev,
            .size = size
        };
        next_free->size = leftover_size - sizeof(struct allocation_t);
        next_free = new_free;
    }
    else
    {
        if (next_free->next)
            next_free->next->prev = next_free->prev;
        if (next_free->prev)
            next_free->prev->next = next_free->next;
        if (area->next_free == next_free)
            area->next_free = next_free->next;
    }
    next_free->next = area->last_full;
    next_free->prev = (struct allocation_t*)0x00;
    if (area->last_full)
        area->last_full->prev = next_free;
    area->last_full = next_free;
    last_area = area;

    return (void*)(((void*)next_free) - next_free->size);
}


typedef void*(*free_finder_t)(struct alloc_area_t*, size_t, size_t);


static void* find_free_in_area(struct alloc_area_t* area, size_t size, size_t ignored)
{
    struct allocation_t* next_free = area->next_free;
    while (next_free)
    {
        if (size <= next_free->size)
        {
            return do_allocate(area, next_free, size);
        }
        next_free = next_free->next;
    }
    return (void*)0x00;
}


static void* find_aligned_free_in_area(struct alloc_area_t* area, size_t size, size_t alignment)
{
    struct allocation_t* next_free = area->next_free;
    while (next_free)
    {
        if (size <= next_free->size)
        {
            void* next_free_base = ((void*)next_free) - next_free->size;
            void* aligned_next_free = (void*)ROUND_UP(next_free_base, alignment);

            if (aligned_next_free + size <= (void*)next_free)
            {
                size_t fragment_size;

                if ((fragment_size = aligned_next_free - next_free_base) >= (sizeof(struct allocation_t) + sizeof(unsigned long)))
                {
                    struct allocation_t* free_fragment = aligned_next_free - sizeof(struct allocation_t);
                    *free_fragment = (struct allocation_t)
                    {
                        .next = next_free,
                        .prev = next_free->prev,
                        .size = fragment_size - sizeof(struct allocation_t)
                    };
                    if (next_free->prev)
                        next_free->prev->next = free_fragment;
                    if (area->next_free == next_free)
                        area->next_free = free_fragment;
                    next_free->prev = free_fragment;
                    next_free->size -= fragment_size;
                    fragment_size = 0;
                }
                void* allocation = do_allocate_lowest(area, next_free, size + fragment_size);
                return (void*) ROUND_UP(allocation, alignment);
            }
        }
        next_free = next_free->next;
    }
    return (void*)0x00;
}


static void* free_from_area(struct alloc_area_t* area, void* ptr)
{
    for (struct allocation_t* allocation_i = area->last_full; allocation_i; allocation_i = allocation_i->next)
    {
        if (ptr < (void*)allocation_i && ptr >= ((void*)allocation_i) - allocation_i->size)
        {
            if (allocation_i->prev)
                allocation_i->prev->next = allocation_i->next;
            if (allocation_i->next)
                allocation_i->next->prev = allocation_i->prev;
            if (area->next_free)
                area->next_free->prev = allocation_i;
            if (allocation_i == area->last_full)
                area->last_full = allocation_i->next;
            allocation_i->prev = (struct allocation_t*)0x00;
            allocation_i->next = area->next_free;
            area->next_free = allocation_i;
            return allocation_i;
        }
    }
    return 0;
}


static struct allocation_t* free_with_return(void* ptr)
{
    struct allocation_t* old_allocation;
    if (ptr < (void*)last_area && ptr >= last_area->area)
        if ((old_allocation = free_from_area(last_area, ptr)))
            return old_allocation;
    for (struct alloc_area_t* area_i = head_area; area_i; area_i = area_i->next_area)
        if (ptr < (void*)area_i && ptr >= area_i->area)
            if ((old_allocation = free_from_area(area_i, ptr)))
                return old_allocation;
    // __asm("movq %0, (%%rax)" : : "r" (ptr), "a" (0));
    __asm("int3;");
    return (struct allocation_t*)0x00;
    // _exit(42 + 1);
}


static void* aligned_or_not_malloc(size_t size, free_finder_t free_finder, size_t alignment)
{
    size = ROUND_UP(size, sizeof(struct allocation_t));
    void* allocation;

    if (__glibc_unlikely(!head_area))
        init_heap();
    
    if (__glibc_unlikely(size > DEFAULT_AREA_SIZE) || __glibc_unlikely(size + alignment > DEFAULT_AREA_SIZE))
    {
        struct alloc_area_t* area = new_alloc_area(last_area, alignment + size);
        if ((allocation = free_finder(area, size, alignment)))
            return allocation;
        __asm("int3;");
        return (void*)0x00;
    }

    if (last_area->next_free)
    {
        if ((allocation = free_finder(last_area, size, alignment)))
            return allocation;
    }


    struct alloc_area_t* area = head_area;
    while (area)
    {
        if ((allocation = free_finder((last_area = area), size, alignment)))
            return allocation;
        area = area->next_area;
    }

    last_area = new_alloc_area(last_area, DEFAULT_AREA_SIZE);
    if ((allocation = free_finder(last_area, size, alignment)))
        return allocation;
    
    __asm("int3;");
    return (void*)0x00;
}


#ifdef TEST_BUILD
void* __pmvee_malloc(size_t size)
#else
void* malloc(size_t size)
#endif
{
    return aligned_or_not_malloc(size, &find_free_in_area, 0);
}


#ifdef TEST_BUILD
void __pmvee_free(void* ptr)
#else
void free(void* ptr)
#endif
{
    if (!ptr)
        return;
    if (ptr < (void*)last_area && ptr >= last_area->area)
        if (free_from_area(last_area, ptr))
            return;
    for (struct alloc_area_t* area_i = head_area; area_i; area_i = area_i->next_area)
        if (ptr < (void*)area_i && ptr >= area_i->area)
            if (free_from_area(area_i, ptr))
                return;
    // TODO: we're leaking memory here, I think.
    return;
}


#ifdef TEST_BUILD
void* __pmvee_calloc(size_t nmemb, size_t size)
#else
void* calloc(size_t nmemb, size_t size)
#endif
{
    #ifdef TEST_BUILD
    void* allocation = __pmvee_malloc(nmemb * size);
    #else
    void* allocation = malloc(nmemb * size);
    #endif
    memset(allocation, 0, nmemb * size);
    return allocation;
}


#ifdef TEST_BUILD
void* __pmvee_realloc(void *ptr, size_t size)
#else
void* realloc(void *ptr, size_t size)
#endif
{
    #ifdef TEST_BUILD
    void* new_allocation = __pmvee_malloc(size);
    #else
    void* new_allocation = malloc(size);
    #endif
    memset(new_allocation, 0, size);
    if (ptr)
    {
        struct allocation_t* old_allocation = free_with_return(ptr);
        memcpy(new_allocation, ((void*)old_allocation) - old_allocation->size, old_allocation->size < size ? old_allocation->size : size);
    }
    return new_allocation;
}


#ifdef TEST_BUILD
void* __pmvee_memalign(size_t alignment, size_t size)
#else
void* memalign(size_t alignment, size_t size)
#endif
{
    // printf(" > memalign: %zu @ %zu\n", size, alignment);
    return aligned_or_not_malloc(size, &find_aligned_free_in_area, alignment);
}


#ifdef TEST_BUILD
int __pmvee_posix_memalign(void **memptr, size_t alignment, size_t size)
#else
int posix_memalign(void **memptr, size_t alignment, size_t size)
#endif
{
    void* allocated = memalign(alignment, size);
    if (allocated)
        *memptr = allocated;
    return allocated ? 0 : 1;
}


#if defined(PMVEE_LEADER) || defined(PMVEE_FOLLOWER)
void __pmvee_state_migration_pmvee_allocator(char* __pmvee_zone, size_t* __pmvee_args_size, void* origin)
{
    PMVEE_STATE_COPY_POINTER(head_area);
    PMVEE_STATE_COPY_POINTER(last_area);
}
#endif