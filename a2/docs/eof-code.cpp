#include <iostream>
#include <string>
int main()
{
    std::string s = "";
    s += EOF;
    std::cout << s << std::endl;
    return 0;
}