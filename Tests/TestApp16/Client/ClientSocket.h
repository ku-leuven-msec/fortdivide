/*
 * Definition of the ClientSocket class
 * Source: http://linuxgazette.net/issue74/tougher.html
 */

#ifndef ClientSocket_class
#define ClientSocket_class

#include "Socket.h"


class ClientSocket : private Socket
{
 public:

  ClientSocket ( std::string host, int port );
  virtual ~ClientSocket(){};

  const ClientSocket& operator << ( const std::string& ) const;
  const ClientSocket& operator >> ( std::string& ) const;

  bool getpeername( std::string&, int& );

};


#endif
