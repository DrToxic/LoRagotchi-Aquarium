// Pipe-driven host boundary for cross-language integration tests. This compiles
// the production Receiver, but mocks flash/radio: never label it hardware proof.
#include "examples/companion_radio/LoRagotchiRX.h"
struct Backend:lrx::IO {
  uint32_t hash=100;
  bool save(const lrx::Journal& j) override {return lrx::valid(j);}
  bool send(const uint8_t*,const char*,uint32_t& ack) override {ack=++hash;return true;}
};
int main(){
  Backend backend;lrx::Receiver receiver(backend);receiver.begin(nullptr,0);
  uint8_t key[32]={1},rx[32]={3};
  for(uint8_t i=1;i<=2;i++){
    key[0]=i;uint32_t now=(i-1)*6000;
    receiver.receive(key,"LFG1|REQ|7|8|2|Host fixture",now);
    receiver.receive(key,"LFG1|COMMIT|7|8|C|1|3|5|2016",now+1);
    receiver.tick(now+4001);receiver.acknowledgeRadio(backend.hash);
  }
  int lead;
  while((lead=getchar())!=EOF){
    if(lead!='<')continue;int lo=getchar(),hi=getchar();if(lo<0||hi<0)return 1;
    size_t length=unsigned(lo)|(unsigned(hi)<<8);if(!length || length>176)return 2;
    uint8_t request[176],response[176];if(fread(request,1,length,stdin)!=length)return 3;
    size_t size;
    if(request[0]==10){response[0]=10;size=1;}
    else size=receiver.command(request,length,response,11000,rx,1);
    if(!size)return 4;putchar('>');putchar(size&255);putchar(size>>8);fwrite(response,1,size,stdout);fflush(stdout);
  }
}
