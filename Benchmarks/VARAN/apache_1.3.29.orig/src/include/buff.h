/* ====================================================================
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 2000-2003 The Apache Software Foundation.  All rights
 * reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 *
 * 3. The end-user documentation included with the redistribution,
 *    if any, must include the following acknowledgment:
 *       "This product includes software developed by the
 *        Apache Software Foundation (http://www.apache.org/)."
 *    Alternately, this acknowledgment may appear in the software itself,
 *    if and wherever such third-party acknowledgments normally appear.
 *
 * 4. The names "Apache" and "Apache Software Foundation" must
 *    not be used to endorse or promote products derived from this
 *    software without prior written permission. For written
 *    permission, please contact apache@apache.org.
 *
 * 5. Products derived from this software may not be called "Apache",
 *    nor may "Apache" appear in their name, without prior written
 *    permission of the Apache Software Foundation.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 * ====================================================================
 *
 * This software consists of voluntary contributions made by many
 * individuals on behalf of the Apache Software Foundation.  For more
 * information on the Apache Software Foundation, please see
 * <http://www.apache.org/>.
 *
 * Portions of this software are based upon public domain software
 * originally written at the National Center for Supercomputing Applications,
 * University of Illinois, Urbana-Champaign.
 */

#ifndef APACHE_BUFF_H
#define APACHE_BUFF_H

#ifdef __cplusplus
extern "C" {
#endif

#ifdef B_SFIO
#include "sfio.h"
#endif

#include <stdarg.h>

/* Reading is buffered */
#define B_RD     (1)
/* Writing is buffered */
#define B_WR     (2)
#define B_RDWR   (3)
/* At end of file, or closed stream; no further input allowed */
#define B_EOF    (4)
/* No further output possible */
#define B_EOUT   (8)
/* A read error has occurred */
#define B_RDERR (16)
/* A write error has occurred */
#define B_WRERR (32)
#ifdef B_ERROR  /* in SVR4: sometimes defined in /usr/include/sys/buf.h */
#undef B_ERROR
#endif
#define B_ERROR (48)
/* Use chunked writing */
#define B_CHUNK (64)
/* bflush() if a read would block */
#define B_SAFEREAD (128)
/* buffer is a socket */
#define B_SOCKET (256)
#ifdef CHARSET_EBCDIC
#define B_ASCII2EBCDIC 0x40000000  /* Enable conversion for this buffer */
#define B_EBCDIC2ASCII 0x80000000  /* Enable conversion for this buffer */
#endif /*CHARSET_EBCDIC*/

typedef struct buff_struct BUFF;

struct buff_struct {
    int flags;			/* flags */
    unsigned char *inptr;	/* pointer to next location to read */
    int incnt;			/* number of bytes left to read from input buffer;
				 * always 0 if had a read error  */
    int outchunk;		/* location of chunk header when chunking */
    int outcnt;			/* number of byte put in output buffer */
    unsigned char *inbase;
    unsigned char *outbase;
    int bufsiz;
    void (*error) (BUFF *fb, int op, void *data);
    void *error_data;
    long int bytes_sent;	/* number of bytes actually written */

    ap_pool *pool;

/* could also put pointers to the basic I/O routines here */
    int fd;			/* the file descriptor */
    int fd_in;			/* input file descriptor, if different */
#ifdef WIN32
    HANDLE hFH;			/* Windows filehandle */
#endif

    /* transport handle, for RPC binding handle or some such */
    void *t_handle;

#ifdef B_SFIO
    Sfio_t *sf_in;
    Sfio_t *sf_out;
#endif

    void *callback_data;
    void (*filter_callback)(BUFF *, const void *, int );
	
};

#ifdef B_SFIO
typedef struct {
    Sfdisc_t disc;
    BUFF *buff;
} apache_sfio;

extern Sfdisc_t *bsfio_new(pool *p, BUFF *b);
#endif

/* Options to bset/getopt */
#define BO_BYTECT (1)

/* Stream creation and modification */
API_EXPORT(BUFF *) ap_bcreate(pool *p, int flags);
API_EXPORT(void) ap_bpushfd(BUFF *fb, int fd_in, int fd_out);
#ifdef WIN32
API_EXPORT(void) ap_bpushh(BUFF *fb, HANDLE hFH);
#endif
API_EXPORT(int) ap_bsetopt(BUFF *fb, int optname, const void *optval);
API_EXPORT(int) ap_bgetopt(BUFF *fb, int optname, void *optval);
API_EXPORT(int) ap_bsetflag(BUFF *fb, int flag, int value);
API_EXPORT(int) ap_bclose(BUFF *fb);

#define ap_bgetflag(fb, flag)	((fb)->flags & (flag))

/* Error handling */
API_EXPORT(void) ap_bonerror(BUFF *fb, void (*error) (BUFF *, int, void *),
			  void *data);

/* I/O */
API_EXPORT(int) ap_bread(BUFF *fb, void *buf, int nbyte);
API_EXPORT(int) ap_bgets(char *s, int n, BUFF *fb);
API_EXPORT(int) ap_blookc(char *buff, BUFF *fb);
API_EXPORT(int) ap_bskiplf(BUFF *fb);
API_EXPORT(int) ap_bwrite(BUFF *fb, const void *buf, int nbyte);
API_EXPORT(int) ap_bflush(BUFF *fb);
API_EXPORT(int) ap_bputs(const char *x, BUFF *fb);
API_EXPORT_NONSTD(int) ap_bvputs(BUFF *fb,...);
API_EXPORT_NONSTD(int) ap_bprintf(BUFF *fb, const char *fmt,...)
				__attribute__((format(printf,2,3)));
API_EXPORT(int) ap_vbprintf(BUFF *fb, const char *fmt, va_list vlist);

/* Internal routines */
API_EXPORT(int) ap_bflsbuf(int c, BUFF *fb);
API_EXPORT(int) ap_bfilbuf(BUFF *fb);

#ifndef CHARSET_EBCDIC

#define ap_bgetc(fb)   ( ((fb)->incnt == 0) ? ap_bfilbuf(fb) : \
		    ((fb)->incnt--, *((fb)->inptr++)) )

#define ap_bputc(c, fb) ((((fb)->flags & (B_EOUT|B_WRERR|B_WR)) != B_WR || \
		     (fb)->outcnt == (fb)->bufsiz) ? ap_bflsbuf(c, (fb)) : \
		     ((fb)->outbase[(fb)->outcnt++] = (c), 0))

#else /*CHARSET_EBCDIC*/

#define ap_bgetc(fb)   ( ((fb)->incnt == 0) ? ap_bfilbuf(fb) : \
		    ((fb)->incnt--, (fb->flags & B_ASCII2EBCDIC)\
		    ?os_toebcdic[(unsigned char)*((fb)->inptr++)]:*((fb)->inptr++)) )

#define ap_bputc(c, fb) ((((fb)->flags & (B_EOUT|B_WRERR|B_WR)) != B_WR || \
		     (fb)->outcnt == (fb)->bufsiz) ? ap_bflsbuf(c, (fb)) : \
		     ((fb)->outbase[(fb)->outcnt++] = (fb->flags & B_EBCDIC2ASCII)\
		     ?os_toascii[(unsigned char)c]:(c), 0))

#endif /*CHARSET_EBCDIC*/
struct child_info {
#ifdef WIN32
    /*
     *  These handles are used by ap_call_exec to call 
     *  create process with pipe handles.
     */
    HANDLE hPipeInputRead;
    HANDLE hPipeOutputWrite;
    HANDLE hPipeErrorWrite;
#else
    /* 
     * We need to put a dummy member in here to avoid compilation
     * errors under certain Unix compilers, like SGI's and HPUX's,
     * which fail to compile a zero-sized struct.  Of course
     * it would be much nicer if there was actually a use for this
     * structure under Unix.  Aah the joys of x-platform code.
     */
    int dummy;
#endif
};
API_EXPORT(int) ap_bspawn_child(pool *, int (*)(void *, child_info *), void *,
					enum kill_conditions, BUFF **pipe_in, BUFF **pipe_out,
					BUFF **pipe_err);

/* enable non-blocking operations */
API_EXPORT(int) ap_bnonblock(BUFF *fb, int direction);
/* and get an fd to select() on */
API_EXPORT(int) ap_bfileno(BUFF *fb, int direction);

/* bflush() if a read now would block, but don't actually read anything */
API_EXPORT(void) ap_bhalfduplex(BUFF *fb);

#if defined(WIN32) || defined(NETWARE) || defined(CYGWIN_WINSOCK) 

/* ap_recvwithtimeout/ap_sendwithtimeout socket primitives for WinSock */
API_EXPORT(int) ap_sendwithtimeout(int sock, const char *buf, int len, int flags);
API_EXPORT(int) ap_recvwithtimeout(int sock, char *buf, int len, int flags);

#endif

#ifdef __cplusplus
}
#endif

#endif	/* !APACHE_BUFF_H */
